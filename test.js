doFibonacci = function (base, n) {
    addFactory = function () {
        add = function (a, b) {
            return a + b
        }
        return add
    }
    addition = addFactory()
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
    return fibonacci(n, addition)
}
for (i = 5; i < 15; i = i + 1)
    print doFibonacci(3, i)
return 0