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
for (i = 4; i < 12; i = i + 1) {
    print fibonacci(i, add)
}
return 0