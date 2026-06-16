import { SolveWorkbench } from "../components/SolveWorkbench";

export default async function WorkspacePage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string }>;
}) {
  const resolvedSearchParams = await searchParams;

  return <SolveWorkbench mode="workspace" initialQuery={resolvedSearchParams?.q} />;
}
