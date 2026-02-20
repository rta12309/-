import { useState } from 'react';
import type { Group } from '../types/models';

interface Props {
  groups: Group[];
  activeGroupId: string;
  onSelect: (id: string) => void;
  onAdd: (name: string) => void;
  onRename: (id: string, name: string) => void;
  onDelete: (id: string) => void;
}

export const GroupList = ({ groups, activeGroupId, onSelect, onAdd, onRename, onDelete }: Props) => {
  const [name, setName] = useState('');

  return (
    <section className="panel">
      <h2>GroupList</h2>
      <div className="group-list">
        {groups.map((group) => (
          <div key={group.id} className={`group-item ${group.id === activeGroupId ? 'active' : ''}`}>
            <button onClick={() => onSelect(group.id)}>{group.name}</button>
            <button onClick={() => {
              const renamed = prompt('새 그룹 이름', group.name);
              if (renamed) onRename(group.id, renamed);
            }}>이름변경</button>
            <button onClick={() => onDelete(group.id)}>삭제</button>
          </div>
        ))}
      </div>
      <div className="inline-form">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="새 그룹 이름" />
        <button onClick={() => {
          if (name.trim()) {
            onAdd(name.trim());
            setName('');
          }
        }}>그룹 추가</button>
      </div>
    </section>
  );
};
