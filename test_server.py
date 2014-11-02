import zmq
import json

port = 9000
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:%s" % port)

class APIError(Exception):
    pass

def _rpc_foo(**kw):
    print 'Calling phone {0}'.format(kw)
    return {'out_a' : 5,
            'out_b' : {'y' : 10},
            'out_bla2' : [{'y' : 5}, {'y' : 3}]}

_api_calls = {'_rpc_foo' : _rpc_foo}

def _error(reason):
    return json.dumps({'__status' : -1,
                       'reason' : reason})

def _success(result):
    result.update({'__status' : 1})
    return json.dumps(result)

while True:
    #  Wait for next request from client
    message = socket.recv()
    j = json.loads(message)
    function_name = j['__api_name']
    print "Received request: ", message

    if function_name not in _api_calls.keys():
        result = _error('No API named {0}'.format(function_name))
    else:
        try:
            del j['__api_name']
            api_result = _api_calls[function_name](**j)
            if not api_result:
                api_reuslt = {}
        except APIError as e:
            result = _error(repr(e))
        else:
            result = _success(api_result)

    print result
    socket.send(result)
