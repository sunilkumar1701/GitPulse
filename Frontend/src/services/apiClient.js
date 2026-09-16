import axios from "axios";
import { supabase } from "./supabaseClient";

const apiClient = axios.create({
  baseURL:
    import.meta.env.VITE_API_URL ||
    "http://localhost:5000/api",

  timeout: 30000,

  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use(
  async (config) => {
    try {
      const { data } = await supabase.auth.getSession();
      const token = data?.session?.access_token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error("Error fetching Supabase session for API request:", error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);


apiClient.interceptors.response.use(
  (response) => response,

  (error) => {
    if (error.code === "ECONNABORTED") {
      return Promise.reject({
        status: 408,
        message: "Request timed out.",
      });
    }

    if (!error.response) {
      return Promise.reject({
        status: 503,
        message: "Backend server is unavailable.",
      });
    }

    const { status, data } = error.response;

    return Promise.reject({
      status,

      message:
        data?.message ||
        data?.error ||
        "Something went wrong.",
    });
  },
);

export default apiClient;