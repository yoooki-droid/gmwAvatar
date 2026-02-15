import { createBrowserRouter } from "react-router";
import { EditorPage } from "./pages/EditorPage";
import { ListPage } from "./pages/ListPage";
import { RootLayout } from "./components/RootLayout";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: RootLayout,
    children: [
      { index: true, Component: ListPage },
      { path: "editor", Component: EditorPage },
      { path: "editor/:id", Component: EditorPage },
    ],
  },
]);
