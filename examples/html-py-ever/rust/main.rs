//! Pure rust version for comparing with python based calls

use scraper::{Html, Selector};

use std::env;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

fn main() {
    let path = PathBuf::from(
        env::args()
            .nth(1)
            .expect("You need to pass the file name as first argument"),
    );

    let now = Instant::now();
    let html_string = fs::read_to_string(&path).unwrap();
    let document = Html::parse_document(&html_string);
    println!("{:?}", now.elapsed());

    let now2 = Instant::now();
    let selector = Selector::parse("a[href]").unwrap();
    let links: Vec<String> = document
        .select(&selector)
        .map(|element| element.text().collect())
        .collect();
    println!("{} {:?}", links.len(), now2.elapsed());
}
