class A:
    def a1(self):
        print(f"A.a1({self})")

    def a2(self, x):
        print(f"A.a2({self}, {x})")

a = A()
a.a1()
getattr(A, "a1")(a)
a.a2("Hello")
getattr(A, "a2")(a, "Hello")

def method(obj, method, *args, **kargs):
    return getattr(obj.__class__, method)(obj, *args, **kargs)

method(a, "a1")
method(a, "a2", "Hello")

getattr(a, "a1")()
getattr(a, "a2")("Hello")

# That all works, showing how flexible Python is.
# In C++/Qt there is little equivalence, although SOME methods are
# available via metaobjects.
# To "simulate" something like this in C++/Qt I could write a whole
# pile of access functions. That might be more straightforward than
# writing customized wrapper classes and using metaobjects ...

def A_a1(a: A):
    return a.a1()

def A_a2(a: A, x):
    return a.a2(x)

A_a1(a)
A_a2(a, "Hello")

# The class name of an object is available in the metaobject system, so
# this could be extracted and used to look up the prefix (rather than
# providing it explicitly), but this only works with direct class matches,
# not with subclasses, etc. Perhaps that is good enough, though?
# A really fancy mechanism go go up the class hierarchy looking for
# method matches ...

'''
// Function taking 2 parameters
// and returning sum
auto sum = [&](int a, int b) {  // What does '&' do???
    return a + b;
};

// Call the function using variables
cout << "The sum is: "
     << sum(4, 5);
'''

