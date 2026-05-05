import { Routes, Route, Link } from "react-router-dom";
import styles from "./App.module.css";
import CallQueue from "./components/CallQueue";
import CallDetail from "./components/CallDetail";
import Stats from "./components/Stats";

export default function App() {
  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <div className={styles.headerDot} />
        <h1>
          <Link to="/" style={{ textDecoration: "none", color: "inherit" }}>
            Call Review System
          </Link>
        </h1>
      </header>

      <main className={styles.main}>
        <Routes>
          <Route
            path="/"
            element={
              <>
                <Stats />
                <CallQueue />
              </>
            }
          />
          <Route path="/calls/:id" element={<CallDetail />} />
        </Routes>
      </main>
    </div>
  );
}
