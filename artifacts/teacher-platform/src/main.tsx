import { createRoot } from "react-dom/client";
import { setBaseUrl } from "@workspace/api-client-react";

import App from "./App";
import "./index.css";

// const apiUrl = import.meta.env.VITE_API_URL;

// // Development -> use Vite proxy (/api)
// // Production -> use Render backend
// if (apiUrl) {
//   setBaseUrl(apiUrl);
// }
setBaseUrl("https://guruz-backend.onrender.com");  

createRoot(document.getElementById("root")!).render(<App />);
