import React from 'react';
import { Autocomplete, TextField } from '@mui/material';
import { useCompanies } from '../../hooks/useAgents';

interface Props {
  value: string;
  onChange: (company: string) => void;
  label?: string;
}

const CompanySelect: React.FC<Props> = ({ value, onChange, label = 'Target company' }) => {
  const { data } = useCompanies();
  const names = (data?.companies ?? []).map((c) => c.name);

  return (
    <Autocomplete
      freeSolo
      size="small"
      options={names}
      value={value}
      onInputChange={(_, newValue) => onChange(newValue)}
      renderInput={(params) => <TextField {...params} label={label} sx={{ minWidth: 260 }} />}
    />
  );
};

export default CompanySelect;
