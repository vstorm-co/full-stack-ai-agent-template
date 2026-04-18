{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Project } from "@/types/project";

interface ProjectState {
  projects: Project[];
  activeProjectId: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setProjects: (projects: Project[]) => void;
  addProject: (project: Project) => void;
  updateProject: (project: Project) => void;
  removeProject: (projectId: string) => void;
  setActiveProject: (projectId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  getActiveProject: () => Project | null;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      projects: [],
      activeProjectId: null,
      isLoading: false,
      error: null,

      setProjects: (projects) => set({ projects }),

      addProject: (project) =>
        set((state) => ({ projects: [project, ...state.projects] })),

      updateProject: (project) =>
        set((state) => ({
          projects: state.projects.map((p) =>
            p.id === project.id ? project : p
          ),
        })),

      removeProject: (projectId) =>
        set((state) => ({
          projects: state.projects.filter((p) => p.id !== projectId),
          activeProjectId:
            state.activeProjectId === projectId
              ? null
              : state.activeProjectId,
        })),

      setActiveProject: (projectId) => set({ activeProjectId: projectId }),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error }),

      getActiveProject: () => {
        const { projects, activeProjectId } = get();
        if (!activeProjectId) return null;
        return projects.find((p) => p.id === activeProjectId) ?? null;
      },
    }),
    {
      name: "project-store",
      partialize: (state) => ({ activeProjectId: state.activeProjectId }),
    }
  )
);
{%- endif %}
