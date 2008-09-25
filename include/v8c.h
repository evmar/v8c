
#ifdef __cplusplus
extern "C" {
typedef v8::HandleScope V8HandleScope;
typedef v8::Handle<void> V8Handle;
typedef const v8::Arguments& V8Arguments;
typedef v8::ExtensionConfiguration* V8ExtensionConfiguration;
typedef v8::String::Utf8Value V8StringUtf8Value;
typedef v8::TryCatch V8TryCatch;
#else  // Compiling on the C side.
typedef int bool;
typedef struct _V8HandleScope V8HandleScope;
typedef struct _V8Handle {
  void* value;  // Needs to match v8::Handle.
} V8Handle;
typedef struct _V8Arguments* V8Arguments;
typedef void* V8ExtensionConfiguration;
typedef void V8StringUtf8Value;
typedef struct _V8TryCatch V8TryCatch;
#endif

void v8_set_flags_from_command_line(int* argc, char** argv,
                                    bool remove_flags);

/* HandleScope */
V8HandleScope* v8_handle_scope_new();
void           v8_handle_scope_free(V8HandleScope* hs);

/* String */
V8Handle v8_string_new_utf8(const char* data, int length);

/* FunctionTemplate */
V8Handle v8_function_template_new(V8Handle (*function)(const V8Arguments));

/* ObjectTemplate */
V8Handle v8_object_template_new();

/* Template */
void v8_template_set(V8Handle tmpl, V8Handle name, V8Handle value);

/* Context */
V8Handle v8_context_new(V8ExtensionConfiguration extensions,
                        V8Handle global_template);
void v8_context_enter(V8Handle context);
void v8_context_exit(V8Handle context);

/* Script */
V8Handle v8_script_compile(V8Handle source);
V8Handle v8_script_run(V8Handle script);

/* Handle */
bool v8_handle_is_empty(V8Handle handle);

/* Arguments */
int v8_arguments_length(V8Arguments args);
V8Handle v8_arguments_get(V8Arguments args, int i);

/* Utf8Value */
V8StringUtf8Value* v8_string_utf8_value_new(V8Handle handle);
int v8_string_utf8_value_length(V8StringUtf8Value* utf8);
char* v8_string_utf8_value_chars(V8StringUtf8Value* utf8);
void v8_string_utf8_value_free(V8StringUtf8Value* utf8);

/* TryCatch */
V8TryCatch* v8_try_catch_new();
void v8_try_catch_free(V8TryCatch* try_catch);
bool v8_try_catch_has_caught(V8TryCatch* try_catch);
V8Handle v8_try_catch_exception(V8TryCatch* try_catch);
V8Handle v8_try_catch_get_message(V8TryCatch* try_catch);
void v8_try_catch_reset(V8TryCatch* try_catch);
void v8_try_catch_set_verbose(V8TryCatch* try_catch, bool value);

#ifdef __cplusplus
}
#endif
