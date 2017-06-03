# MiniScript

## What is MiniScript? 

It is a programming language inspired mainly by JavaScript and blended with some features in C, Python and Lua. It is flexible, elegant and powerful. 

### First glimpse of MiniScript

#### Hello World

```javascript
print "Hello World!"
return 0
```

Note that all the programs should end with a return statement (or the program will run into an error). Similarly, all the functions in MiniScritpt should end with a return statement

#### Fibonacci

```javascript
fibonacci = function (n) {
    if (n > 2)
    {
        result =  fibonacci(n - 1) +  fibonacci(n - 2)
    }
    else
    {
        result =  1
    }
    return result
}
print fibonacci(10)
return 0
```

Note that functions are defined with something like lambda expressions. Recursive functions are supported.

Functions can be passed to functions like a value, so the Fibonacci example can be rewritten as:

```javascript
fibonacci = function (n, method) {
    if (n > 2)
    {
        result =  method(fibonacci(n - 1), method), fibonacci(n - 2, method))
    }
    else
    {
        result =  1
    }
    return result
}
add = function(a, b){
    return a + b
}
print fibonacci(10, add)
return 0
```

Also, functions can be returned from another function, which gives wise to our third Fibonacci example

```javascript
fibonacci = function (n, method) {
    if (n > 2)
    {
        result =  method(fibonacci(n - 1), method), fibonacci(n - 2, method))
    }
    else
    {
        result =  1
    }
    return result
}
print fibonacci(10, function(){
    return function(a, b){
        return a + b
    }
}())
return 0
```

#### Student

MiniScript provides minimal support for object-oriented programming, based on prototype-based inheritance.

```javascript
Student = {
    "teacher": "fengyan",
    "new": function(name){
        student = {}
        student.name = name
        student.prototype = Student
        return student
    },
    "setName": function (self, name) {
        self.name = name return 0
    },
    "setTeacher": function (self, teacher) {
        self.teacher = teacher return 0
    }
}
Boy = {
    "prototype": Student,
    "new": function (name) {
        boy = Student.new(name)
        boy.prototype = Boy
        return boy
    }
}
boy1 = Boy.new("Tom")
boy2 = Boy.new("David")
boy1.setName(boy1, "Tomas")
print boy1.name + " " + boy1.teacher + " " + boy2.name + " " + boy2.teacher
boy2.setTeacher(boy2, "chenchun")
print boy1.name + " " + boy1.teacher + " " + boy2.name + " " + boy2.teacher
return 0
```

Here, We take advantage to prototype based inheritance to mimic the class based object-class relation and inheritance. Boy is inherited from Student, and both boy1 and boy2 are instances of Boy.





