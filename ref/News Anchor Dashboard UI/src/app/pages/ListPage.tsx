import { useState } from "react";
import { Link } from "react-router";
import { Edit, Trash2, Eye, Plus } from "lucide-react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

interface NewsItem {
  id: string;
  status: "published" | "draft";
  title: string;
  speaker: string;
  date: string;
}

export function ListPage() {
  const [newsItems] = useState<NewsItem[]>([
    {
      id: "1",
      status: "published",
      title: "Annual Technology Summit Highlights Innovation Trends",
      speaker: "Sarah Johnson",
      date: "2026-02-10",
    },
    {
      id: "2",
      status: "draft",
      title: "Economic Policy Changes Announced for Q2",
      speaker: "Michael Chen",
      date: "2026-02-09",
    },
    {
      id: "3",
      status: "published",
      title: "Healthcare Initiative Launches Nationwide",
      speaker: "Emily Rodriguez",
      date: "2026-02-08",
    },
    {
      id: "4",
      status: "published",
      title: "Environmental Summit Addresses Climate Goals",
      speaker: "David Thompson",
      date: "2026-02-07",
    },
    {
      id: "5",
      status: "draft",
      title: "Education Reform Proposals Under Review",
      speaker: "Lisa Anderson",
      date: "2026-02-06",
    },
  ]);

  return (
    <div className="max-w-[1800px] mx-auto px-6 py-8">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-semibold text-black">News Items</h1>
          <p className="text-gray-600 mt-1">Manage your broadcast content</p>
        </div>
        <Link to="/editor">
          <Button className="bg-black hover:bg-gray-800 text-white">
            <Plus size={16} className="mr-2" />
            New Item
          </Button>
        </Link>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50 hover:bg-gray-50">
              <TableHead className="font-semibold text-gray-700">Status</TableHead>
              <TableHead className="font-semibold text-gray-700">Title</TableHead>
              <TableHead className="font-semibold text-gray-700">Speaker</TableHead>
              <TableHead className="font-semibold text-gray-700">Date</TableHead>
              <TableHead className="font-semibold text-gray-700 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {newsItems.map((item) => (
              <TableRow key={item.id} className="hover:bg-gray-50">
                <TableCell>
                  <Badge
                    variant={item.status === "published" ? "default" : "secondary"}
                    className={
                      item.status === "published"
                        ? "bg-green-100 text-green-800 hover:bg-green-100"
                        : "bg-gray-100 text-gray-800 hover:bg-gray-100"
                    }
                  >
                    {item.status === "published" ? "Published" : "Draft"}
                  </Badge>
                </TableCell>
                <TableCell className="font-medium text-gray-900 max-w-md">
                  {item.title}
                </TableCell>
                <TableCell className="text-gray-600">{item.speaker}</TableCell>
                <TableCell className="text-gray-600">
                  {new Date(item.date).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-gray-600 hover:text-black hover:bg-gray-100"
                    >
                      <Eye size={16} />
                    </Button>
                    <Link to={`/editor/${item.id}`}>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-gray-600 hover:text-black hover:bg-gray-100"
                      >
                        <Edit size={16} />
                      </Button>
                    </Link>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-gray-600 hover:text-red-600 hover:bg-red-50"
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Footer Stats */}
      <div className="mt-6 text-sm text-gray-600">
        Showing {newsItems.length} items
      </div>
    </div>
  );
}
