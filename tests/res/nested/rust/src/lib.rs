#[repr(C)]
pub struct Point {
    pub x: f32,
    pub y: f32,
}

#[repr(u32)]
pub enum Foo {
    A = 1,
    B,
    C
}

#[no_mangle]
pub unsafe extern "C" fn example_get_origin() -> Point {
    Point { x: 0.0, y: 0.0 }
}

#[no_mangle]
pub unsafe extern "C" fn example_print_foo(foo: *const Foo) {
    println!("{}", match *foo {
        Foo::A => "a",
        Foo::B => "b",
        Foo::C => "c",
    });
}
