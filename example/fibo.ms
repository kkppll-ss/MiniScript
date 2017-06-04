fibonacci = function(n: int){
    last = 1
    next_to_last = 0
    for (i = 0; i < n; i = i + 1) {
        current = last + next_to_last
        next_to_last = last
        last = current
        if (current > 30)
            break
    }
    return current
}
for (n = 3; n < 20; n = n + 1) {
    print fibonacci(n)
}
return 0