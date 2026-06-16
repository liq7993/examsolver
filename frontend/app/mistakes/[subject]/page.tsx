import { MistakesClient } from "../MistakesClient";

type MistakeSubjectPageProps = {
  params: Promise<{
    subject: string;
  }>;
};

export default async function MistakeSubjectPage({ params }: MistakeSubjectPageProps) {
  const { subject } = await params;

  return <MistakesClient subject={decodeURIComponent(subject)} />;
}
