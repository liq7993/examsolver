import { NotePageClient } from "./NotePageClient";

type NotePageProps = {
  params: Promise<{
    solve_id: string;
  }>;
};

export default async function NotePage({ params }: NotePageProps) {
  const { solve_id: solveId } = await params;

  return <NotePageClient solveId={solveId} />;
}
