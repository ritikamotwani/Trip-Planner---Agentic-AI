import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './components/LandingPage';
import MessyMindChat from './components/Conversational/MessyMindChat';
import TripPlannerForm from './components/PersonalItinerary/TripPlannerForm';
import PersonalItinerary from './components/PersonalItinerary/PersonalItinerary';

function App() {
  return (
    <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/chat" element={<MessyMindChat />} />
          <Route path="/personal-itinerary" element={<TripPlannerForm />} />
          <Route path="/personal-itinerary/plan" element={<PersonalItinerary />} />
        </Routes>
    </Router>
  );
}

export default App;
