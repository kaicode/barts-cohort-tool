import React, { useState } from 'react';
import { AsyncTypeahead } from 'react-bootstrap-typeahead';
import Form from 'react-bootstrap/Form';

const SnomedSearch = (args) => {

  const [code, setCode] = useState([]);
  const [mustHave, setMustHave] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [options, setOptions] = useState([]);
  const [includedCodeCount, setincludedCodeCount] = useState("");

  const handleSearch = (query) => {
    setIsLoading(true);
    setincludedCodeCount("");
    // Replace with actual API call
    fetch(`/api/snomed/search?ecl=<<${args.target_code}&term=${query}`)
      .then(response => response.json())
      .then(data => {
        setOptions(data.expansion.contains || []);

        setIsLoading(false);
      });
  };

  const selectCode = (selected) => {
    setCode(selected);
    if (args.onSelect) {
      args.onSelect({
          code: selected,
          mustHave: mustHave
      });
    }
    if (selected.length === 1) {
      setincludedCodeCount("");
      fetch(`/api/snomed/count-descendants-and-self?code=${selected[0].code}`)
          .then(response => response.json())
          .then(data => {
            setincludedCodeCount(data.expansion.total || "");
          });
      console.log(getSelection())
    }
  };

  const changeMustHave = (mustHave) => {
    setMustHave(mustHave)
    if (args.onSelect) {
      args.onSelect({
          code: code,
          mustHave: mustHave
      });
    }
  }

  return (
  <div>
    <Form.Group className="mb-3">
      <Form.Label>{args.label}</Form.Label>
      <Form.Check type="radio" id={'must_have_' + args.label} label="Must have" checked={mustHave} onChange={() => changeMustHave(true)} />
      <Form.Check type="radio" id={'must_not_have_' + args.label} label="Must not have" checked={!mustHave} onChange={() => changeMustHave(false)} />
      <AsyncTypeahead
        id={args.label}
        labelKey="display"
        options={options}
        isLoading={isLoading}
        onSearch={handleSearch}
        placeholder="Search for something..."
        selected={code}
        onChange={selectCode}
      />
      <p><i>{(includedCodeCount !== "") &&<span>Includes {includedCodeCount} code</span>}{(includedCodeCount > 1) && <span>s</span>}</i></p>
    </Form.Group>
  </div>
  );
};

export default SnomedSearch;
