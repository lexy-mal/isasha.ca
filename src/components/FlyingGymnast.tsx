import { Card } from "./ui/card";
import { Zap } from "lucide-react";

export function FlyingGymnast() {
  return (
    <section className="py-20 px-6 bg-white">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-12">
          <Zap className="w-8 h-8 text-purple-600" />
          <h2 className="text-4xl text-purple-900">Flying Gymnast</h2>
        </div>
        
        <Card className="p-10 bg-gradient-to-br from-purple-50 via-pink-50 to-orange-50 border-purple-200 hover:shadow-lg transition-shadow">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <span className="text-3xl">🤸‍♀️✨</span>
              <h3 className="text-2xl text-purple-900">Acrobatic Gymnastics</h3>
            </div>
            <p className="text-purple-700 text-lg">
              I also really enjoy my individual acrobatic gymnastics lessons. They help me recover from my injury and make me stronger every week.
            </p>
            <p className="text-purple-700 text-lg">
              These lessons teach me amazing skills — and they even help me when I perform as a "flying gymnast" on stage or in shows.
            </p>
          </div>
        </Card>
      </div>
    </section>
  );
}