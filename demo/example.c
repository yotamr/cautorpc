#include <jansson.h>
#include <string.h>
#include "cautorpc.h"
#include "example_structs.h"
#include "example.h"
int _rpc_foo(enum bla_e a, int bla, struct my_struct_s s, int *out_a, struct some_other_struct_s *out_b,
             struct some_other_struct_s **out_bla2, int *out_bla2_size)
{
	int rc = -1;
	json_t *obj = json_object();
	json_object_set(obj, "__api_name", json_string("_rpc_foo"));
	json_object_set(obj, "a", json_integer(a));
	json_object_set(obj, "s", my_struct_s_to_json(&s));
	json_object_set(obj, "bla", json_integer(bla));
	json_t *result = crpc_make_request(obj);
	if (NULL == result) { goto free_request; };
	json_t *__status_json = json_object_get(result, "__status");
	if (NULL == __status_json)
	{
		fprintf(stderr, "Missing paramater named __status from result\n");
		goto free_result;
	}
	if (CRPC_SUCCESS != json_integer_value(__status_json))
	{
		fprintf(stderr, "Remote API returned an error\n");
		goto free_result;
	}
	json_t *out_a_json = json_object_get(result, "out_a");
	if (NULL == out_a_json)
	{
		fprintf(stderr, "Missing paramater named out_a from result\n");
		goto free_result;
	}
	*out_a = json_integer_value(out_a_json);
	json_t *out_b_json = json_object_get(result, "out_b");
	if (NULL == out_b_json)
	{
		fprintf(stderr, "Missing paramater named out_b from result\n");
		goto free_result;
	}
	rc = some_other_struct_s_from_json(out_b_json, out_b);
	if (0 != rc)
	{
		fprintf(stderr, "Error parsing object parameter out_b\n");
		goto free_result;
	}
	json_t *out_bla2_json = json_object_get(result, "out_bla2");
	if (NULL == out_bla2_json)
	{
		fprintf(stderr, "Missing paramater named out_bla2 from result\n");
		goto free_result;
	}
	size_t out_bla2_array_size = json_array_size(out_bla2_json);
	if (0 == out_bla2_array_size)
	{
		fprintf(stderr, "out_bla2 is not an array\n");
		goto free_result;
	}
	*out_bla2 = (struct some_other_struct_s *)malloc((out_bla2_array_size + 1)* sizeof(**out_bla2));
	for (int i = 0; i < out_bla2_array_size; i++)
	{
		json_t *out_bla2_array_data = json_array_get(out_bla2_json, i);
		rc = some_other_struct_s_from_json(out_bla2_array_data, (*out_bla2 + i));
		if (0 != rc)
		{
			fprintf(stderr, "Error parsing object parameter (*out_bla2 + i)\n");
			goto free_result;
		}
	}
	*out_bla2_size = out_bla2_array_size;
	json_t *out_bla2_size_json = json_object_get(result, "out_bla2_size");
	if (NULL == out_bla2_size_json)
	{
		fprintf(stderr, "Missing paramater named out_bla2_size from result\n");
		goto free_result;
	}
	*out_bla2_size = json_integer_value(out_bla2_size_json);
	free_result:
	json_decref(result);
	free_request:
	json_decref(obj);
	return rc;
}