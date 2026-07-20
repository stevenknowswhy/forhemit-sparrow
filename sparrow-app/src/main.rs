//! Shared Rust code for Sparrow.
//!
//! Currently minimal — the agent logic lives in Python.
//! Future: SQLite storage, native file system access, tray icon.

pub fn app_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert_eq!(app_version(), "0.1.0");
    }
}
