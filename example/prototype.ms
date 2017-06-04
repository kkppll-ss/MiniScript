parent = {
    "change": function (self: table, newValue: int) {
        self.value = newValue
        return 0
    }
}
child = {
    "prototype": parent,
    "value": 3
}
print child.value
child.change(child, 8)
print child.value
child.change = function(self: table, newValue: int){
    self.value = newValue - 1
    return 0
}
child.change(child, 8)
print child.value
print "hello" + "world"
return 0