#define BUILDING_V8C
#include "../include/v8.h"
#include "../include/v8c.h"

template<typename T>
static V8Handle unwrap_handle(v8::Handle<T> handle) {
  return *handle;
}

template<typename T>
static v8::Handle<T> wrap_handle(V8Handle handle) {
  return v8::Handle<T>(reinterpret_cast<T*>(handle));
}

extern "C" {

void v8_set_flags_from_command_line(int* argc, char** argv,
                                    bool remove_flags) {
  v8::V8::SetFlagsFromCommandLine(argc, argv, remove_flags);
}

v8::HandleScope* v8_handle_scope_new() {
  return new v8::HandleScope();
}

void v8_handle_scope_free(V8HandleScope* hs) {
  delete hs;
}

V8Handle v8_string_new_utf8(const char* data, int length) {
  return unwrap_handle(v8::String::New(data, length));
}

int v8_string_length(V8Handle h) {
  return wrap_handle<v8::String>(h)->Length();
}

struct V8InvocationCallbackData {
  V8InvocationCallback callback;
  // TODO: void* data.
};

static v8::Handle<v8::Value> v8_invocation_callback(const v8::Arguments& args) {
  v8::Local<v8::External> data = v8::Local<v8::External>::Cast(args.Data());
  V8InvocationCallbackData* callback_data =
      static_cast<V8InvocationCallbackData*>(data->Value());
  return wrap_handle<v8::Value>(callback_data->callback(&args));
}

V8Handle v8_function_template_new(V8InvocationCallback callback) {
  // XXX this leaks.  We need to somehow tie this lifetime to the
  // function template's lifetime?
  V8InvocationCallbackData* callback_data = new V8InvocationCallbackData;
  callback_data->callback = callback;
  return unwrap_handle(
      v8::FunctionTemplate::New(v8_invocation_callback,
				v8::External::New(callback_data)));
}

V8Handle v8_object_template_new() {
  return unwrap_handle(v8::ObjectTemplate::New());
}

void v8_template_set(V8Handle tmpl, V8Handle name, V8Handle value) {
  wrap_handle<v8::Template>(tmpl)->Set(wrap_handle<v8::String>(name),
                                       wrap_handle<v8::Data>(value));
}

V8Handle v8_context_new(V8ExtensionConfiguration extensions,
                        V8Handle global_template) {
  return unwrap_handle(
      v8::Context::New(extensions,
                       wrap_handle<v8::ObjectTemplate>(global_template)));
}

void v8_context_enter(V8Handle context) {
  wrap_handle<v8::Context>(context)->Enter();
}

void v8_context_exit(V8Handle context) {
  wrap_handle<v8::Context>(context)->Exit();
}

bool v8_handle_is_empty(V8Handle handle) {
  return wrap_handle<void>(handle).IsEmpty();
}

V8Handle v8_undefined() {
  return unwrap_handle(v8::Undefined());
}

V8Handle v8_script_compile(V8Handle code) {
  return unwrap_handle(v8::Script::Compile(wrap_handle<v8::String>(code)));
}

V8Handle v8_script_run(V8Handle script) {
  return unwrap_handle(wrap_handle<v8::Script>(script)->Run());
}

int v8_arguments_length(const V8Arguments* args) {
  return args->Length();
}

V8Handle v8_arguments_get(const V8Arguments* args, int i) {
  return unwrap_handle((*args)[i]);
}

V8StringUtf8Value* v8_string_utf8_value_new(V8Handle handle) {
  return new v8::String::Utf8Value(wrap_handle<v8::Value>(handle));
}

int v8_string_utf8_value_length(V8StringUtf8Value* utf8) {
  return utf8->length();
}

char* v8_string_utf8_value_chars(V8StringUtf8Value* utf8) {
  return **utf8;
}

void v8_string_utf8_value_free(V8StringUtf8Value* utf8) {
  delete utf8;
}

V8TryCatch* v8_try_catch_new() {
  return new V8TryCatch;
}

void v8_try_catch_free(V8TryCatch* try_catch) {
  delete try_catch;
}

bool v8_try_catch_has_caught(V8TryCatch* try_catch) {
  return try_catch->HasCaught();
}

V8Handle v8_try_catch_exception(V8TryCatch* try_catch) {
  return unwrap_handle(try_catch->Exception());
}

V8Handle v8_try_catch_get_message(V8TryCatch* try_catch) {
  return unwrap_handle(try_catch->Message());
}

void v8_try_catch_reset(V8TryCatch* try_catch) {
  try_catch->Reset();
}

void v8_try_catch_set_verbose(V8TryCatch* try_catch, bool value) {
  try_catch->SetVerbose(value);
}

}  // extern "C"
