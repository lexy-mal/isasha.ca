import { Heart } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-gradient-to-br from-purple-600 to-pink-600 text-white py-12 px-6">
      <div className="max-w-6xl mx-auto text-center space-y-4">
        <div className="flex items-center justify-center gap-2">
          <Heart className="w-6 h-6 fill-white" />
          <p className="text-xl">Thank you for visiting my page!</p>
          <Heart className="w-6 h-6 fill-white" />
        </div>
        <p className="text-purple-100">Alexandra Malashenko © 2025</p>
      </div>
    </footer>
  );
}
