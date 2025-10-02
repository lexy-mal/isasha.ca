import { Hero } from "./components/Hero";
import { StorySection } from "./components/StorySection";
import { FlyingGymnast } from "./components/FlyingGymnast";
import { PassionsSection } from "./components/PassionsSection";
import { LookingAhead } from "./components/LookingAhead";
import { Footer } from "./components/Footer";

export default function App() {
  return (
    <div className="min-h-screen">
      <Hero />
      <StorySection />
      <FlyingGymnast />
      <PassionsSection />
      <LookingAhead />
      <Footer />
    </div>
  );
}
