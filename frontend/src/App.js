import './App.css';
import React, { useState, useEffect } from 'react';
import { Button, Form } from "react-bootstrap";
import SnomedSearch from "./components/SnomedSearch";

// Options from config
import { ethnicityOptions, genderOptions, defaultAgeRange } from './config/formOptions';

function App() {
  useEffect(() => {
    document.title = "Patient Cohorting Tool";
  }, []);

  const [title, setTitle] = useState("");
  const [selectedGenders, setSelectedGenders] = useState([]);
  const [minAge, setMinAge] = useState(defaultAgeRange.min);
  const [maxAge, setMaxAge] = useState(defaultAgeRange.max);
  const [ethnicity, setEthnicity] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [mustHaveFindings, setMustHaveFindings] = useState([]);
  const [mustNotHaveFindings, setMustNotHaveFindings] = useState([]);

  const handleEthnicityChange = (code, label) => {
    setEthnicity((prev) => {
      const ethnicityItem = { code, display: label };
      return prev.some(item => item.code === code)
        ? prev.filter(item => item.code !== code)
        : [...prev, ethnicityItem];
    });
  };

  const handleGenderChange = (code, label) => {
    setSelectedGenders((prev) => {
      const genderItem = { code, display: label };
      return prev.some(item => item.code === code)
        ? prev.filter(item => item.code !== code)
        : [...prev, genderItem];
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    console.log("🔍 mustHaveFindings on submit:", mustHaveFindings); // << add this line

    const cohortDefinition = {
      title,
      gender: selectedGenders.length === 0 ? "ALL" : selectedGenders,
      ageRange: { min: minAge, max: maxAge },
      ethnicity: ethnicity.length === 0 ? "ALL" : ethnicity,
      timeRange: {
        ...(startDate && { start: startDate }),
        ...(endDate && { end: endDate }),
      },
      mustHaveFindings,
      mustNotHaveFindings,
    };

    try {
      const response = await fetch('/api/cohort/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cohortDefinition)
      });

      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      console.log(data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div style={{ margin: '20px', maxWidth: '600px' }}>
      <h1>Cohort Builder</h1>
      <p>Use this form to create a cohort by defining the selection criteria.</p>

      <Form onSubmit={handleSubmit}>
        <Form.Group className="mb-3" controlId="title">
          <Form.Label>Cohort Title</Form.Label>
          <Form.Control type="text" placeholder="Title" onChange={(e) => setTitle(e.target.value)} />
          <Form.Text className="text-muted">Use a short descriptive title.</Form.Text>
        </Form.Group>

        <Form.Group className="mb-3" controlId="gender">
          <Form.Label>Gender</Form.Label>
          {genderOptions.map(({ code, label }) => (
            <Form.Check
              key={code}
              type="checkbox"
              label={label}
              checked={selectedGenders.some(item => item.code === code)}
              onChange={() => handleGenderChange(code, label)}
            />
          ))}
          <Form.Text className="text-muted">Leave blank to include all genders.</Form.Text>
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Minimum Age: {minAge}</Form.Label>
          <Form.Range min={0} max={120} value={minAge} onChange={(e) => setMinAge(Number(e.target.value))} />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Maximum Age: {maxAge}</Form.Label>
          <Form.Range min={0} max={120} value={maxAge} onChange={(e) => setMaxAge(Number(e.target.value))} />
        </Form.Group>

        <Form.Group className="mb-3" controlId="ethnicity">
          <Form.Label>Ethnicity</Form.Label>
          {ethnicityOptions.map(({ code, label }) => (
            <Form.Check
              key={code}
              type="checkbox"
              label={label}
              checked={ethnicity.some(item => item.code === code)}
              onChange={() => handleEthnicityChange(code, label)}
            />
          ))}
          <Form.Text className="text-muted">Leave blank to include all ethnicities.</Form.Text>
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Time Range (optional)</Form.Label>
          <Form.Control
            type="date"
            placeholder="Start Date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <Form.Control
            type="date"
            placeholder="End Date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={{ marginTop: "5px" }}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Must HAVE Finding / Disorder</Form.Label>
          <SnomedSearch
            label=""
            target_code="404684003"
            onSelect={(snomedSelection) => {
              const newCode = snomedSelection.code.code || snomedSelection.code[0]?.code;
              
              // 🔍 Log all SNOMED codes with details
              // console.log("snomedSelection:", snomedSelection.codesWithDetails);
      
              setMustHaveFindings((prev) =>
                prev.some(item => (item.code.code || item.code[0]?.code) === newCode)
                  ? prev
                  : [...prev, snomedSelection]
              );        
            }}
          />
          
          {mustHaveFindings.length > 0 && (
            <ul style={{ marginTop: "10px", paddingLeft: "20px" }}>
            
              {mustHaveFindings.map((item, index) => {
                const displayValue = item.code?.display || item.code?.[0]?.display;
                const count = item.count || 1;
                const uniqueId = item.code?.code || item.code?.[0]?.code;

                if (displayValue && uniqueId) {
                  return (
                    <li key={uniqueId} style={{ marginBottom: "5px" }}>
                        <a
                          href={`https://termbrowser.nhs.uk/?perspective=full&conceptId1=${uniqueId}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ textDecoration: "underline", color: "#007bff" }}
                        >
                          {displayValue}
                        </a>{' '}
                      {`(Included ${count} code${count !== 1 ? 's' : ''})`}
                      <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={() =>
                          setMustHaveFindings(prev =>
                            prev.filter((_, i) => i !== index)
                          )
                        }
                        style={{ marginLeft: "10px", padding: "0 6px" }}
                      >
                        ❌
                      </Button>
                    </li>
                  );
                }
                return null;
              })}
            </ul>
          )}

        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Must NOT HAVE Finding / Disorder</Form.Label>
          <SnomedSearch
            label=""
            target_code="404684003"
            onSelect={(snomedSelection) => {
              const newCode = snomedSelection.code.code || snomedSelection.code[0]?.code;
              setMustNotHaveFindings((prev) =>
                prev.some(item => (item.code.code || item.code[0]?.code) === newCode)
                  ? prev
                  : [...prev, snomedSelection]
              );
            }}
          />

          {mustNotHaveFindings.length > 0 && (
            <ul style={{ marginTop: "10px", paddingLeft: "20px" }}>
              {mustNotHaveFindings.map((item, index) => {
                const displayValue = item.code?.display || item.code?.[0]?.display;
                const count = item.count || 1;
                const uniqueId = item.code?.code || item.code?.[0]?.code;

                if (displayValue && uniqueId) {
                  return (
                    <li key={uniqueId} style={{ marginBottom: "5px" }}>
                        <a
                          href={`https://termbrowser.nhs.uk/?perspective=full&conceptId1=${uniqueId}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ textDecoration: "underline", color: "#007bff" }}
                        >
                          {displayValue}
                        </a>{' '}
                      {`(Included ${count} code${count !== 1 ? 's' : ''})`}
                      <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={() =>
                          setMustNotHaveFindings(prev =>
                            prev.filter((_, i) => i !== index)
                          )
                        }
                        style={{ marginLeft: "10px", padding: "0 6px" }}
                      >
                        ❌
                      </Button>
                    </li>
                  );
                }
                return null;
              })}
            </ul>
          )}

        </Form.Group>

        <Button variant="primary" type="submit">Submit</Button>
      </Form>

      <hr />
      <h5>Summary of Selected Criteria</h5>
      <ul>
        <li><strong>Title:</strong> {title || "N/A"}</li>
        <li><strong>Genders:</strong> {
          selectedGenders.length === 0
            ? "All"
            : selectedGenders
                .map(item => `${item.display}`)
                .join(', ')
        }</li>
        <li><strong>Age Range:</strong> {minAge} - {maxAge}</li>
        <li><strong>Ethnicities:</strong> {
          ethnicity.length === 0
            ? "All"
            : ethnicity
                .map(item => `${item.display}`)
                .join(', ')
        }</li>
        <li><strong>Time Range:</strong> {
          startDate || endDate
            ? `${startDate || "Any"} to ${endDate || "Any"}`
            : "Any"
        }</li>
        <li><strong>Must Have Findings/Disorders:</strong> {
          mustHaveFindings.length === 0
            ? "None"
            : mustHaveFindings
                .map(item => item.code && item.code[0] ? item.code[0].display : null)
                .filter(displayValue => displayValue)
                .join(', ') || "None"
        }</li>
        <li><strong>Must Not Have Findings/Disorders:</strong> {
          mustNotHaveFindings.length === 0
            ? "None"
            : mustNotHaveFindings
                .map(item => item.code && item.code[0] ? item.code[0].display : null)
                .filter(displayValue => displayValue)
                .join(', ') || "None"
        }</li>
      </ul>
    </div>
  );
}

export default App;
