/* Copyright 2007-2008 the V8 project authors. All rights reserved.
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions are
   met:

       * Redistributions of source code must retain the above copyright
         notice, this list of conditions and the following disclaimer.
       * Redistributions in binary form must reproduce the above
         copyright notice, this list of conditions and the following
         disclaimer in the documentation and/or other materials provided
         with the distribution.
       * Neither the name of Google Inc. nor the names of its
         contributors may be used to endorse or promote products derived
         from this software without specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
   OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
   OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/* v8c -- v8 API for using v8 from C (and other languages that can bind against
   C). */

/* NOTE: This file tries to follow include/v8.h directly.  The
   function order should match the order there, and that file should contain
   all the documentation.
*/

/* v8::Handle has a lot of nice type-checking and wrapping and unwrapping,
   but in the C world all we get is a pointer.
   Internally, V8Handle is the pointer held by a v8::Handle.
*/
typedef void* V8Handle;

/* To have the compiler help catch type errors, this file is #included by
   both the C++ implementation and the C user.  These typedefs make the
   function prototypes work on both sides.
 */
#ifdef __cplusplus
extern "C" {
typedef v8::HandleScope V8HandleScope;
typedef v8::Arguments V8Arguments;
typedef v8::ExtensionConfiguration* V8ExtensionConfiguration;
typedef v8::String::Utf8Value V8StringUtf8Value;
typedef v8::TryCatch V8TryCatch;
#else  /* Compiling on the C side. */
typedef int bool;
typedef struct _V8HandleScope V8HandleScope;
typedef struct _V8Arguments V8Arguments;
typedef void* V8ExtensionConfiguration;
typedef void V8StringUtf8Value;
typedef struct _V8TryCatch V8TryCatch;
#endif

/* Handle */
bool v8_handle_is_empty(V8Handle handle);

/* HandleScope */
V8HandleScope* v8_handle_scope_new();
void           v8_handle_scope_free(V8HandleScope* hs);

/* Script */
V8Handle v8_script_compile(V8Handle source);
V8Handle v8_script_run(V8Handle script);

/* String */
V8Handle v8_string_new_utf8(const char* data, int length);

/* String::Utf8Value */
V8StringUtf8Value* v8_string_utf8_value_new(V8Handle handle);
int v8_string_utf8_value_length(V8StringUtf8Value* utf8);
char* v8_string_utf8_value_chars(V8StringUtf8Value* utf8);
void v8_string_utf8_value_free(V8StringUtf8Value* utf8);

/* Template */
void v8_template_set(V8Handle tmpl, V8Handle name, V8Handle value);

/* Arguments */
int v8_arguments_length(const V8Arguments* args);
V8Handle v8_arguments_get(const V8Arguments* args, int i);

/* FunctionTemplate */
/* V8 lets you add a "data" value to a function template, but v8c uses
   it internally.  We could still provide extra-data-like
   functionality if needed, though. */
typedef V8Handle (*V8InvocationCallback)(const V8Arguments*);
V8Handle v8_function_template_new(V8InvocationCallback callback);

/* ObjectTemplate */
V8Handle v8_object_template_new();

/* Special static values */
V8Handle v8_undefined();
V8Handle v8_null();
V8Handle v8_true();
V8Handle v8_false();

/* V8 (class containing static functions) */
void v8_set_flags_from_command_line(int* argc, char** argv,
                                    bool remove_flags);

/* TryCatch */
V8TryCatch* v8_try_catch_new();
void v8_try_catch_free(V8TryCatch* try_catch);
bool v8_try_catch_has_caught(V8TryCatch* try_catch);
V8Handle v8_try_catch_exception(V8TryCatch* try_catch);
V8Handle v8_try_catch_get_message(V8TryCatch* try_catch);
void v8_try_catch_reset(V8TryCatch* try_catch);
void v8_try_catch_set_verbose(V8TryCatch* try_catch, bool value);

/* Context */
V8Handle v8_context_new(V8ExtensionConfiguration extensions,
                        V8Handle global_template);
void v8_context_enter(V8Handle context);
void v8_context_exit(V8Handle context);

#ifdef __cplusplus
}
#endif
