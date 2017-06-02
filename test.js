
print (function (base, n) {
    addFactory = function () {
        add = function (a, b) {
            return a + b
        }
        return add
    }
    fibonacci = function (n, method) {
        if (n > base)
        {
            result =  method(fibonacci(n - 1, method), fibonacci(n - 2, method))
        }
        else
        {
            result =  1
        }
        return result
    }
    return fibonacci(n, addFactory())
})(3, 10)
return 0