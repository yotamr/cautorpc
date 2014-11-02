#############################################################################
#
# Copyright 2014, Yotam Rubin <yotamrubin@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##############################################################################

# TODO: Handle duplicates in parameter names
# Better errors: type mismtaches, differentiate between comm and json errors
# Reserve __status

import sys
from clang import cindex
from clang.cindex import CursorKind as ck
from clang.cindex import TypeKind as tk
from IPython import embed
from clike import *
import click
import os
from autojson import struct_jsonable, StructNotJsonable, struct_serializer_function_name, struct_parser_function_name

class ChildNotParam(Exception):
    pass

class ParameterMustBePointer(Exception):
    pass

class ParameterNotSerializable(Exception):
    pass

class ParameterCannotBePointer(Exception):
    pass

class ParameterMustBeNamed(Exception):
    pass

class MissingSizeOutputForArray(Exception):
    pass

class SizeOutputMustBeInt(Exception):
    pass

_basic_types = [tk.INT]

def _output_parameter(child):
    if child.spelling.startswith('out_'):
        return True
    else:
        return False

def _pointer_type(t):
    return t.get_pointee().kind != tk.INVALID

def _type_serializable(t):
    decl = t.get_declaration()
    if t.kind == tk.UNEXPOSED and decl.kind == ck.STRUCT_DECL:
        if struct_jsonable(decl):
            return True
        else:
           return False

    if decl.kind == ck.ENUM_DECL:
        return True

    if _pointer_type(t) and t.get_pointee().kind == tk.CHAR_S:
        return False

    if t.kind not in _basic_types:
        return False
    else:
        return True

def _verify_output_parameter(n):
    if not _pointer_type(n.type):
        raise OutputParameterMustBePointer(n.displayname)

    pointee = n.type.get_pointee()
    if _pointer_type(pointee):
        if not _type_serializable(pointee.get_pointee()):
            raise ParameterNotSerializable(n.displayname, pointee.kind)
        else:
            return

    if not _type_serializable(pointee):
        raise ParameterNotSerializable(n.displayname, pointee.kind)


def _verify_input_parameter(n):
    if not _type_serializable(n.type):
        raise ParameterNotSerializable(n.displayname, n.type.kind)

def _output_parameter_array(t):
    return t.type.get_pointee().kind == tk.POINTER


def _function_args_serializable(node):
    children = list(node.get_children())
    for index, child in enumerate(children):
        if child.kind != ck.PARM_DECL:
            raise ChildNotParam(node, child.kind)

        if child.type.kind == tk.FUNCTIONPROTO:
            continue

        if not child.displayname:
            raise ParameterMustBeNamed(child)

        if _output_parameter(child):
            _verify_output_parameter(child)
            if _output_parameter_array(child):
                if len(children) == index:
                    raise MissingSizeOutputForArray(child.displayname)
                if children[index + 1].spelling != child.displayname + '_size':
                    raise MissingSizeOutputForArray(child.displayname)
                if children[index + 1].type.get_pointee().kind != tk.INT:
                    raise SizeOutputMustBeInt(child.displayname)
        else:
            _verify_input_parameter(child)

    return True

def _get_function_decls(root):
    functions = []
    def aux(node):
        if node.kind == ck.FUNCTION_DECL:
            if _function_args_serializable(node):
                functions.append(node)
            else:
                raise FunctionArgsNotSerializable(node)

        for node in node.get_children():
            aux(node)

        return functions

    return aux(root)


def _quote(s):
    return '"{0}"'.format(s)

def _init_c_module(h_input, h_serialization):
    m = Module()
    includes = ["<jansson.h>",
                "<string.h>",
                _quote("cautorpc.h"),
                _quote(h_serialization),
                _quote(h_input)]

    for include in includes:
        m.stmt('#include {0}'.format(include), suffix = '')

    return m

def _fini_h_module(m, h_name):
    m.stmt('#endif /* {0} */'.format(h_name), suffix = '')


def _get_function_prototype(function_decl):
    extent = function_decl.extent
    filename = extent.start.file.name
    start_offset = extent.start.offset
    end_offset = extent.end.offset

    return file(filename, 'rb').read()[start_offset:end_offset]

def _serialize_parameter(m, parameter):
    if parameter.type.kind == tk.UNEXPOSED and struct_jsonable(parameter.type.get_declaration()):
        decl = parameter.type.get_declaration()
        serialized_name = '{0}(&{1})'.format(struct_serializer_function_name(decl), parameter.displayname)

    if parameter.type.kind == tk.INT:
        serialized_name = 'json_integer({0})'.format(parameter.displayname)

    if parameter.type.kind == tk.UNEXPOSED and parameter.type.get_declaration().kind == ck.ENUM_DECL:
        serialized_name = 'json_integer({0})'.format(parameter.displayname)

    m.stmt('json_object_set(obj, "{0}", {1})'.format(parameter.displayname, serialized_name))

def _output_error(m, error_message):
    m.stmt('fprintf(stderr, "{0}\\n")'.format(error_message))

def _get_result_memeber(m, key, json_t_ptr):
    m.stmt('json_t *{0} = json_object_get(result, "{1}")'.format(json_t_ptr, key))

    with m.block('if (NULL == {0})'.format(json_t_ptr)):
        _output_error(m, "Missing paramater named {0} from result".format(key))
        m.stmt('goto free_result')

def _parse_array(m, json_name, name, pointee):
    array_size = name + '_array_size'
    m.stmt('size_t {0} = json_array_size({1})'.format(array_size, json_name))
    with m.block('if (0 == {0})'.format(array_size)):
        _output_error(m, '{0} is not an array'.format(name))
        m.stmt('goto free_result')

    m.stmt('*{0} = ({1})malloc(({2} + 1)* sizeof(**{0}))'.format(name, pointee.spelling, array_size))
    with m.block('for (int i = 0; i < {0}; i++)'.format(array_size)):
        array_data_name  = name + '_array_data'
        output_name = '(*{0} + i)'.format(name)
        m.stmt('json_t *{0} = json_array_get({1}, i)'.format(array_data_name, json_name))
        _parse_type(m, array_data_name, output_name, pointee.get_pointee())

    array_size_output = '{0}_size'.format(name)
    m.stmt("*{0} = {1}".format(array_size_output, array_size))

def _parse_type(m, json_name, name, pointee):
    if pointee.kind == tk.UNEXPOSED and struct_jsonable(pointee.get_declaration()):
        decl = pointee.get_declaration()
        m.stmt('rc = {0}({1}, {2})'.format(struct_parser_function_name(decl),
                                                 json_name,
                                                 name))

        with m.block('if (0 != rc)'):
            _output_error(m, 'Error parsing object parameter {0}'.format(name))
            m.stmt('goto free_result')

    if (pointee.kind == tk.INT or
        pointee.kind == tk.UNEXPOSED and pointee.get_declaration().kind == ck.ENUM_DECL):
        m.stmt('*{0} = json_integer_value({1})'.format(name, json_name))

    if pointee.kind == tk.POINTER:
        _parse_array(m, json_name, name, pointee)


def _parse_parameter(m, parameter):
    param_json_name = parameter.displayname + '_json'
    _get_result_memeber(m, parameter.displayname, param_json_name)
    pointee = parameter.type.get_pointee()
    _parse_type(m, param_json_name, parameter.displayname, pointee)


def _input_parameter(parameter):
    if not parameter.displayname.startswith('out_'):
        return True
    else:
        return False

def _output_parameter(parameter):
    return not _input_parameter(parameter)

def _serialize_parameters(m, parameters):
    _parameters = {}
    for parameter in parameters:
        _parameters[parameter.displayname] = parameter

    parameters = _parameters.values()
    for parameter in parameters:
        if _input_parameter(parameter):
            _serialize_parameter(m, parameter)

def _parse_results(m, parameters):
    _get_result_memeber(m, '__status', '__status_json')
    with m.block('if (CRPC_SUCCESS != json_integer_value(__status_json))'):
        _output_error(m, 'Remote API returned an error')
        m.stmt('goto free_result')

    filtered_parameters = list(parameters)
    for index, parameter in enumerate(parameters):
        if not _output_parameter(parameter):
            continue

        if _output_parameter_array(parameter):
            del filtered_parameters[index + 1]

    for parameter in filtered_parameters:
        if not _output_parameter(parameter):
            continue

        _parse_parameter(m, parameter)

    m.stmt('free_result:', suffix='')
    m.stmt('json_decref(result)')


def _generate_function_stub(m, function_decl):
    with m.block(_get_function_prototype(function_decl)):
        m.stmt('int rc = -1')
        m.stmt("json_t *obj = json_object()")
        m.stmt('json_object_set(obj, "__api_name", json_string("{0}"))'.format(function_decl.spelling))
        _serialize_parameters(m, function_decl.get_arguments())
        m.stmt('json_t *result = crpc_make_request(obj)')
        m.stmt('if (NULL == result) { goto free_request; }')
        _parse_results(m, function_decl.get_arguments())
        m.stmt('free_request:', suffix = '')
        m.stmt('json_decref(obj)')
        m.stmt('return rc')


def _generate_code(h_input, c_module):
    i = cindex.Index.create()
    t = i.parse(h_input, args = ["-C"])

    for function_decl in _get_function_decls(t.cursor):
        _generate_function_stub(c_module, function_decl)


@click.command()
@click.argument('h_input', type=click.Path())
@click.argument('h_serialization', type=click.Path())
@click.argument('c_output')
def generate_code(h_input, c_output, h_serialization):

    c_module = _init_c_module(h_input, h_serialization)
    _generate_code(h_input, c_module)

    file(c_output, "wb").write(c_module.render())

if __name__ == '__main__':
    generate_code()
