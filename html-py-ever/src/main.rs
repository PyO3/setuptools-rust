//! Pure rust version for comparing with python based calls

use kuchiki;

use std::env;
use std::path::PathBuf;
use std::time::Instant;
use tendril::stream::TendrilSink;

fn main() {
    let path = PathBuf::from(
        env::args()
            .nth(1)
            .expect("You need to pass the file name as first argument"),
    );

    let now = Instant::now();
    let document = kuchiki::parse_html().from_utf8().from_file(&path).unwrap();
    println!("{:?}", now.elapsed());
    let now2 = Instant::now();
    let links: Vec<String> = document
        .select("a[href]")
        .unwrap()
        .map(|css_match| css_match.text_contents())
        .collect();
    println!("{} {:?}", links.len(), now2.elapsed());
}
