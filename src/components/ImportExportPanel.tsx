import type { ImportExportData } from '../types/models';

interface Props {
  payload: ImportExportData;
  onImport: (payload: ImportExportData) => void;
}

export const ImportExportPanel = ({ payload, onImport }: Props) => {
  const onBackup = () => {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'portfolio-backup.json';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="panel">
      <h2>ImportExport</h2>
      <div className="inline-form">
        <button onClick={onBackup}>JSON 백업</button>
        <label className="file-input">
          JSON 복원
          <input
            type="file"
            accept="application/json"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const text = await file.text();
              const parsed = JSON.parse(text) as ImportExportData;
              onImport(parsed);
            }}
          />
        </label>
      </div>
    </section>
  );
};
