import './App.css';
import React, { useState, useEffect } from 'react';
import {Button, Form} from "react-bootstrap";
import SnomedSearch from "./components/SnomedSearch";

function App() {
  useEffect(() => {
    document.title = "Cohort Builder";
  }, []);

  const [title, setTitle] = useState(true);
  const [female, setFemale] = useState(true);
  const [male, setMale] = useState(true);
  const [minAge, setMinAge] = useState(18);
  const [maxAge, setMaxAge] = useState(100);
  const [findingSelection, setFindingSelection] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();

    const cohortDefinition = {
      title,
      gender: {
        female,
        male
      },
      ageRange: {
        min: minAge,
        max: maxAge
      },
      findingSelection: findingSelection
    };

    try {
      const response = await fetch('/api/cohort/select', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(cohortDefinition)
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      console.log(data);
    } catch (error) {
      console.error('Error:', error);
    }
  };


    return (
    <div style={{margin: 20 + 'px', maxWidth: 600 + 'px'}}>
      <h1>Cohort Builder</h1>

      <p>Use this form to create a cohort by defining the selection criteria.</p>

      <Form onSubmit={handleSubmit}>

      <Form.Group className="mb-3" controlId="title">
        <Form.Label>Cohort Title</Form.Label>
        <Form.Control type="text" placeholder="Title" onChange={(e) => setTitle(e.target.value)}/>
        <Form.Text className="text-muted">
          Use a short descriptive title.
        </Form.Text>
      </Form.Group>

      <Form.Group className="mb-3" controlId="gender">
        <Form.Label>Gender</Form.Label>
        <Form.Check id="female" type="checkbox" label="Female" checked={female} onChange={() => setFemale(!female)} />
        <Form.Check id="male" type="checkbox" label="Male" checked={male} onChange={() => setMale(!male)} />
        <Form.Text className="text-muted">
          Select all that apply.
        </Form.Text>
      </Form.Group>

      <Form.Group className="mb-3" controlId="age">
        <Form.Label>Minimum Age: {minAge}</Form.Label>
        <Form.Range placeholder="Title" min={0} max={120} value={minAge} onChange={(e) => setMinAge(e.target.value)}/>
      </Form.Group>

      <Form.Group className="mb-3" controlId="age">
        <Form.Label>Maximum Age: {maxAge}</Form.Label>
        <Form.Range placeholder="Title" min={0} max={120} value={maxAge} onChange={(e) => setMaxAge(e.target.value)}/>
      </Form.Group>

      <SnomedSearch label="Finding / Disorder" target_code="404684003" onSelect={(snomedSelection) => setFindingSelection(snomedSelection)}></SnomedSearch>

      <Button variant="primary" type="submit">
        Submit
      </Button>

      </Form>
    </div>
  );
}

export default App;
