import { useEffect, useState } from 'react';

interface Project {
  name: string;
  url: string;
}

export function MyProgrammingProjects() {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    // Scan for HTML files in the projects directory
    const loadProjects = async () => {
      try {
        // In production, you'll need to manually list projects or use a build-time plugin
        const projectFiles = [
          { name: 'Hello World', url: '/projects/HelloWorld.html' }
        ];
        setProjects(projectFiles);
      } catch (error) {
        console.error('Error loading projects:', error);
      }
    };

    loadProjects();
  }, []);

  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-100 py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-4xl md:text-5xl font-bold text-purple-900 mb-4">
            My Programming Projects 💻
          </h2>
          <p className="text-purple-700 text-lg">
            Check out the cool things I've built!
          </p>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-purple-600 text-xl">
              No projects yet... but I'm working on it! 🚀
            </p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project, index) => (
              <a
                key={index}
                href={project.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group relative bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-purple-400/10 to-pink-400/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative p-8">
                  <div className="text-4xl mb-4">🎨</div>
                  <h3 className="text-2xl font-bold text-purple-900 mb-2 group-hover:text-purple-600 transition-colors">
                    {project.name}
                  </h3>
                  <p className="text-purple-600 group-hover:text-purple-800 transition-colors">
                    Click to view project →
                  </p>
                </div>
              </a>
            ))}
          </div>
        )}

        <div className="mt-12 text-center">
          <div className="inline-block px-6 py-3 bg-purple-100 rounded-full border border-purple-200">
            <p className="text-purple-700">
              💡 <strong>Tip:</strong> Drop any HTML file in <code className="bg-purple-200 px-2 py-1 rounded">public/projects/</code> to add it here!
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
