fibonacci = function (n: int) {
    if (n > 2)
    {
        result =  fibonacci(n - 1) + fibonacci(n - 2)
    }
    else
    {
        result =  1
    }
    return result
}
print fibonacci(8)
return 0