#include "include/v8c.h"
#include <stdio.h>

const bool true = 1;
const bool false = 0;

// A callback from JavaScript to print verbosely.
static V8Handle debug_print_cb(const V8Arguments args) {
  int i, length = v8_arguments_length(args);
  printf("debug_print called with %d args\n", length);
  for (i = 0; i < length; ++i) {
    V8StringUtf8Value* utf8 =
        v8_string_utf8_value_new(v8_arguments_get(args, i));
    printf("%d: %s\n", i, v8_string_utf8_value_chars(utf8));
    v8_string_utf8_value_free(utf8);
  }
}

// A callback from JavaScript to print concisely.
static V8Handle print_cb(const V8Arguments args) {
  int i, length = v8_arguments_length(args);
  for (i = 0; i < length; ++i) {
    V8StringUtf8Value* utf8 =
        v8_string_utf8_value_new(v8_arguments_get(args, i));
    if (i > 0)
      printf(" ");
    printf("%s", v8_string_utf8_value_chars(utf8));
    v8_string_utf8_value_free(utf8);
  }
  printf("\n");
}

void report_exception(V8TryCatch* try_catch) {
  V8HandleScope* handle_scope = v8_handle_scope_new();
  V8StringUtf8Value* exception =
      v8_string_utf8_value_new(v8_try_catch_exception(try_catch));
  printf("%s\n", v8_string_utf8_value_chars(exception));
  v8_string_utf8_value_free(exception);
  v8_handle_scope_free(handle_scope);
}

int main(int argc, char** argv) {
  V8HandleScope* handle_scope;
  V8Handle print, debug_print, global, context, script;
  V8TryCatch* try_catch;

  v8_set_flags_from_command_line(&argc, argv, true);

  if (argc < 2) {
    printf("usage: %s <javascript>\n", argv[0]);
    return 1;
  }
  const char* code = argv[1];

  handle_scope = v8_handle_scope_new();
  print = v8_function_template_new(print_cb);
  debug_print = v8_function_template_new(debug_print_cb);
  global = v8_object_template_new();
  v8_template_set(global, v8_string_new_utf8("debug_print", -1), debug_print);
  v8_template_set(global, v8_string_new_utf8("print", -1), print);

  context = v8_context_new(NULL, global);
  v8_context_enter(context);

  try_catch = v8_try_catch_new();
  script = v8_script_compile(v8_string_new_utf8(code, -1));
  if (v8_handle_is_empty(script)) {
    report_exception(try_catch);
  } else {
    V8Handle result = v8_script_run(script);
    if (v8_handle_is_empty(result))
      report_exception(try_catch);
  }
  v8_try_catch_free(try_catch);

  v8_context_exit(context);
  v8_handle_scope_free(handle_scope);

  return 0;
}
