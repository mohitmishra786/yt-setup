fn main() {
    let data = String::from("heap bytes");
    let view = &data;
    drop(data);
    println!("{view}");
}
