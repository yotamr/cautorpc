#include "example.h"
#include "example_structs.h"
json_t *my_struct_s_to_json(const struct my_struct_s *this)
{
	json_t *obj = json_object();
	json_object_set(obj, "x", json_integer(this->x));
	return obj;
}
int my_struct_s_from_json(json_t *json, struct my_struct_s *out)
{
	int rc = json_unpack(json, "{s:i}", "x", &out->x);
	if (0 != rc) { return rc;};
	return 0;
}
json_t *some_other_struct_s_to_json(const struct some_other_struct_s *this)
{
	json_t *obj = json_object();
	json_object_set(obj, "y", json_integer(this->y));
	return obj;
}
int some_other_struct_s_from_json(json_t *json, struct some_other_struct_s *out)
{
	int rc = json_unpack(json, "{s:i}", "y", &out->y);
	if (0 != rc) { return rc;};
	return 0;
}