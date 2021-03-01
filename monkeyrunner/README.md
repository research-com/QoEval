
# Known Errors
## Error when generating help.html
Currently, autogenerating help fails since the classloader does not find the .cs files (style sheets).

Workaround: Unzip the monkeyrunner-*.jar file located in Sdk/tools/lib, move the *.cs files located in the resource folder to com/android/monkeyrunner and zip again.


```
qoe-user@qoemu-01:~/qoemu/monkeyrunner$ ./help.py 
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions] Script terminated due to an exception
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]Traceback (most recent call last):
  File "/home/qoe-user/qoemu/monkeyrunner/./help.py", line 6, in <module>
    text = MonkeyRunner.help("html");
	at com.google.clearsilver.jsilver.resourceloader.ClassLoaderResourceLoader.openOrFail(ClassLoaderResourceLoader.java:76)
	at com.google.clearsilver.jsilver.interpreter.LoadingTemplateFactory.find(LoadingTemplateFactory.java:39)
	at com.google.clearsilver.jsilver.interpreter.OptimizingTemplateFactory.find(OptimizingTemplateFactory.java:67)
	at com.google.clearsilver.jsilver.interpreter.InterpretedTemplateLoader.load(InterpretedTemplateLoader.java:52)
	at com.google.clearsilver.jsilver.JSilver.render(JSilver.java:252)
	at com.google.clearsilver.jsilver.JSilver.render(JSilver.java:267)
	at com.google.clearsilver.jsilver.JSilver.render(JSilver.java:278)
	at com.android.monkeyrunner.MonkeyRunnerHelp.helpString(MonkeyRunnerHelp.java:149)
	at com.android.monkeyrunner.MonkeyRunner.help(MonkeyRunner.java:111)
	at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
	at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
	at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
	at java.lang.reflect.Method.invoke(Method.java:498)

com.google.clearsilver.jsilver.exceptions.JSilverTemplateNotFoundException: com.google.clearsilver.jsilver.exceptions.JSilverTemplateNotFoundException: No class loader resource 'html.cs' in 'com/android/monkeyrunner'

210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.Py.JavaError(Py.java:495)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.Py.JavaError(Py.java:488)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.PyReflectedFunction.__call__(PyReflectedFunction.java:188)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.PyReflectedFunction.__call__(PyReflectedFunction.java:204)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.PyObject.__call__(PyObject.java:387)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.PyObject.__call__(PyObject.java:391)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.pycode._pyx0.f$0(/home/qoe-user/qoemu/monkeyrunner/./help.py:10)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.pycode._pyx0.call_function(/home/qoe-user/qoemu/monkeyrunner/./help.py)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.PyTableCode.call(PyTableCode.java:165)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.PyCode.call(PyCode.java:18)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.Py.runCode(Py.java:1275)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.__builtin__.execfile_flags(__builtin__.java:522)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.util.PythonInterpreter.execfile(PythonInterpreter.java:225)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.android.monkeyrunner.ScriptRunner.run(ScriptRunner.java:116)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.android.monkeyrunner.MonkeyRunnerStarter.run(MonkeyRunnerStarter.java:77)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.android.monkeyrunner.MonkeyRunnerStarter.main(MonkeyRunnerStarter.java:189)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]Caused by: com.google.clearsilver.jsilver.exceptions.JSilverTemplateNotFoundException: No class loader resource 'html.cs' in 'com/android/monkeyrunner'
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.google.clearsilver.jsilver.resourceloader.ClassLoaderResourceLoader.openOrFail(ClassLoaderResourceLoader.java:76)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.google.clearsilver.jsilver.interpreter.LoadingTemplateFactory.find(LoadingTemplateFactory.java:39)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.google.clearsilver.jsilver.interpreter.OptimizingTemplateFactory.find(OptimizingTemplateFactory.java:67)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.google.clearsilver.jsilver.interpreter.InterpretedTemplateLoader.load(InterpretedTemplateLoader.java:52)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.google.clearsilver.jsilver.JSilver.render(JSilver.java:252)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.google.clearsilver.jsilver.JSilver.render(JSilver.java:267)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.google.clearsilver.jsilver.JSilver.render(JSilver.java:278)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.android.monkeyrunner.MonkeyRunnerHelp.helpString(MonkeyRunnerHelp.java:149)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at com.android.monkeyrunner.MonkeyRunner.help(MonkeyRunner.java:111)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at java.lang.reflect.Method.invoke(Method.java:498)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	at org.python.core.PyReflectedFunction.__call__(PyReflectedFunction.java:186)
210227 23:02:04.558:S [main] [com.android.monkeyrunner.MonkeyRunnerOptions]	... 13 more
```