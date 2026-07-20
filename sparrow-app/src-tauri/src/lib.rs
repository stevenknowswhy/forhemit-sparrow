//! Sparrow Tauri library — the core app logic.
//!
//! Wires up the Tauri builder with the frontend.
//! The Python agent runs as a separate HTTP server on localhost:8765.
//! The Tauri frontend communicates with it via fetch() calls.

use tauri::Manager;

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            #[cfg(debug_assertions)]
            {
                let window = app.get_webview_window("main").unwrap();
                window.open_devtools();
                window.close_devtools();
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
