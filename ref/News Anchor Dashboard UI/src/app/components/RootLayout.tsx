import { Outlet, Link, useLocation } from "react-router";
import { FileText, List } from "lucide-react";

export function RootLayout() {
  const location = useLocation();
  const isEditorPage = location.pathname.includes("editor");

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-[1800px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <h1 className="text-xl font-semibold text-black">News Anchor CMS</h1>
            <nav className="flex items-center gap-1">
              <Link
                to="/"
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  !isEditorPage
                    ? "bg-gray-100 text-black"
                    : "text-gray-600 hover:text-black hover:bg-gray-50"
                }`}
              >
                <List size={16} />
                List
              </Link>
              <Link
                to="/editor"
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  isEditorPage
                    ? "bg-gray-100 text-black"
                    : "text-gray-600 hover:text-black hover:bg-gray-50"
                }`}
              >
                <FileText size={16} />
                Editor
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <Outlet />
    </div>
  );
}
