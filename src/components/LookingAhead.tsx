import { Card } from "./ui/card";
import { Rocket, Trophy, Sparkles } from "lucide-react";

export function LookingAhead() {
  return (
    <section className="py-20 px-6 bg-white">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-12">
          <Rocket className="w-8 h-8 text-purple-600" />
          <h2 className="text-4xl text-purple-900">Looking Ahead</h2>
        </div>
        
        <Card className="p-10 bg-gradient-to-br from-purple-100 via-pink-100 to-purple-100 border-purple-300">
          <div className="space-y-6 text-center">
            <div className="flex justify-center gap-4">
              <Trophy className="w-12 h-12 text-purple-600" />
              <Sparkles className="w-12 h-12 text-pink-600" />
            </div>
            <p className="text-purple-800 text-lg">
              Right now, I'm focused on getting even better at dancing, skating, and acrobatics, and maybe winning some medals 🏅.
            </p>
            <p className="text-purple-800 text-lg">
              But no matter what, I want to keep learning, exploring, and having fun.
            </p>
          </div>
        </Card>
      </div>
    </section>
  );
}
