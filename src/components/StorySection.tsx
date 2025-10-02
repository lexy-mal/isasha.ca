import { Card } from "./ui/card";
import { Sparkles, Music, Snowflake } from "lucide-react";

export function StorySection() {
  return (
    <section className="py-20 px-6 bg-white">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-12">
          <Sparkles className="w-8 h-8 text-purple-600" />
          <h2 className="text-4xl text-purple-900">My Story</h2>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8">
          <Card className="p-8 bg-gradient-to-br from-pink-50 to-purple-50 border-purple-200 hover:shadow-lg transition-shadow">
            <div className="flex items-start gap-4">
              <div className="bg-purple-100 p-3 rounded-full">
                <Music className="w-6 h-6 text-purple-600" />
              </div>
              <div className="space-y-4">
                <h3 className="text-2xl text-purple-900">Dance 🩰</h3>
                <p className="text-purple-700">
                  I started rhythmic gymnastics when I was just 3 years old, and it became my first experience in the competitive sports world. I did rhythmic for almost 5 years, and during that time it felt like my whole life was built around ribbons, hoops, and competitions.
                </p>
                <p className="text-purple-700">
                  Later, I had to stop because of an injury, but that turned out to be the start of something even more exciting — dance!
                </p>
                <p className="text-purple-700">
                  Now I'm happier than ever, twirling, spinning, and moving to music. I'm hoping to start competing soon, and I can't wait to show what I've learned.
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-8 bg-gradient-to-br from-blue-50 to-purple-50 border-purple-200 hover:shadow-lg transition-shadow">
            <div className="flex items-start gap-4">
              <div className="bg-blue-100 p-3 rounded-full">
                <Snowflake className="w-6 h-6 text-blue-600" />
              </div>
              <div className="space-y-4">
                <h3 className="text-2xl text-purple-900">Figure Skating ⛸️</h3>
                <p className="text-purple-700">
                  Another sport that has always been part of my life is figure skating. I've been skating since I was 2 years old!
                </p>
                <p className="text-purple-700">
                  I love the feeling of flying across the ice, practicing jumps, and showing off graceful moves.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}
