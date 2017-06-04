Fibonacci = {
    "new": function (method: function) {
        fib = {}
        fib.method = method
        fib.prototype = Fibonacci
        return fib
    },
    "changeMethod": function (self: table, method: function) {self.method = method return 0},
    "performFibonacci" : function(self: table, n: int){
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
        return fibonacci(n, self.method)
    }
}
fibFunction = Fibonacci.new(function (a: int, b: int) { return a + b})
print fibFunction.performFibonacci(fibFunction, 8)
fibFunction.changeMethod(fibFunction, function (a: int, b: int) { return a + 2 * b})
print fibFunction.performFibonacci(fibFunction, 8)
return 0