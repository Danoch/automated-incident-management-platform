const express = require("express");
const sqlite3 = require("sqlite3").verbose();
const dotenv = require("dotenv");
const cors = require("cors");

dotenv.config();
const app = express();
const port = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());

// Connecting to  SQLite
const db = new sqlite3.Database("./database.sqlite", (err) => {
  if (err) {
    console.error("Error al abrir la base de datos", err.message);
  } else {
    console.log("✅ Conectado a SQLite");

    // Crear tabla si no existe
    db.run(
      "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE)",
      (err) => {
        if (err) {
          console.error("Error creando tabla", err.message);
        } else {
          console.log("✅ Tabla 'users' lista");
        }
      }
    );
  }
});

// Ruta principal
app.get("/", (req, res) => {
  res.json({ message: "🚀 API SQLite is working" });
});

// Get users
app.get("/users", (req, res) => {
  db.all("SELECT * FROM users", [], (err, rows) => {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    res.json(rows);
  });
});

// Insert an user
app.post("/users", (req, res) => {
  const { name, email } = req.body;
  db.run("INSERT INTO users (name, email) VALUES (?, ?)", [name, email], function (err) {
    if (err) {
      res.status(400).json({ error: err.message });
      return;
    }
    res.json({ id: this.lastID, name, email });
  });
});

// Start server
app.listen(port, "0.0.0.0", () => {
  console.log(`🚀 Server running in  http://localhost:${port}`);
});
