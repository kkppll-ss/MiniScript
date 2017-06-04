fibonacci = function (n: int, method: function) {
    if (n > 2)
    {
        result =  method(fibonacci(n - 1, method), fibonacci(n - 2, method))
    }
    else
    {
        result =  1
    }
    return result
}
add = function(a: int, b: int){
    return a + b
}
print fibonacci(8, add)
return 0