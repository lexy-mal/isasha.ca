import { Card } from "./ui/card";
import { Heart, Sparkles, Theater, Brain, Plane, PawPrint } from "lucide-react";

export function PassionsSection() {
  const passions = [
    {
      icon: Sparkles,
      title: "Horses & Riding",
      description: "Horses are my favorite animals in the whole world. 🐎 I ride as often as I can, and being at the stables makes me feel free and happy.",
      color: "from-amber-50 to-orange-50",
      iconBg: "bg-amber-100",
      iconColor: "text-amber-700"
    },
    {
      icon: Theater,
      title: "Stage & StarSchool",
      description: "I love acting and performing! ⭐ Through my StarSchool activities, I've been on stage with other actors and even performed solo. Being in the spotlight is exciting!",
      color: "from-pink-50 to-purple-50",
      iconBg: "bg-pink-100",
      iconColor: "text-pink-700"
    },
    {
      icon: Brain,
      title: "Chess",
      description: "I enjoy the challenge of chess and the way every move is like solving a little puzzle. ♟️",
      color: "from-purple-50 to-indigo-50",
      iconBg: "bg-purple-100",
      iconColor: "text-purple-700"
    },
    {
      icon: Plane,
      title: "Traveling",
      description: "Exploring new places makes me curious and inspired.",
      color: "from-blue-50 to-cyan-50",
      iconBg: "bg-blue-100",
      iconColor: "text-blue-700"
    },
    {
      icon: PawPrint,
      title: "Animals",
      description: "I love all animals, especially dogs and cats... but horses will always have the biggest piece of my heart. 🐶🐱🐴",
      color: "from-green-50 to-emerald-50",
      iconBg: "bg-green-100",
      iconColor: "text-green-700"
    }
  ];

  return (
    <section className="py-20 px-6 bg-gradient-to-br from-purple-50 to-pink-50">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-12">
          <Heart className="w-8 h-8 text-purple-600" />
          <h2 className="text-4xl text-purple-900">My Passions</h2>
        </div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {passions.map((passion, index) => (
            <Card 
              key={index}
              className={`p-6 bg-gradient-to-br ${passion.color} border-purple-200 hover:shadow-lg transition-all hover:-translate-y-1`}
            >
              <div className="space-y-4">
                <div className={`${passion.iconBg} p-3 rounded-full w-fit`}>
                  <passion.icon className={`w-6 h-6 ${passion.iconColor}`} />
                </div>
                <h3 className="text-xl text-purple-900">{passion.title}</h3>
                <p className="text-purple-700">{passion.description}</p>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
