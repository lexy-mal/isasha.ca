import profileImage from 'figma:asset/4ace55cbee8e2ee463d045b7eff12e440412aac1.png';

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-purple-50 via-pink-50 to-purple-100 py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div className="order-2 md:order-1 space-y-6">
            <div className="inline-block px-4 py-2 bg-white/80 backdrop-blur-sm rounded-full border border-purple-200">
              <span className="text-purple-600">Welcome to my page! 🌸</span>
            </div>
            <h1 className="text-5xl md:text-6xl text-purple-900">
              Hi, I'm Sasha!
            </h1>
            <div className="space-y-4">
              <p className="text-purple-800 text-lg">
                My name is <span className="text-purple-600">Alexandra</span> (some people call me Sasha) <span className="text-purple-600">Malashenko</span>.
              </p>
              <p className="text-purple-700 text-lg">
                I'm 8 years old, and I love trying new things, moving, and learning every single day! ✨
              </p>
            </div>
            <div>
              <a
                href="#my-programming-projects"
                className="inline-block px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-full border-2 border-purple-300 hover:border-purple-400 transition-all duration-300 hover:shadow-lg hover:scale-105 font-medium"
              >
                My Programming Projects 💻
              </a>
            </div>
          </div>
          <div className="order-1 md:order-2 flex justify-center">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-400 to-pink-400 rounded-3xl blur-2xl opacity-30 transform scale-95"></div>
              <img 
                src={profileImage} 
                alt="Alexandra Malashenko" 
                className="relative rounded-3xl shadow-2xl w-full max-w-md object-cover"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
