import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Tooltip, Button } from '@mui/material';
import styled from '@emotion/styled';
import { Link } from 'react-router-dom';

import "./LandingPage.css";
import parisImg from "../assets/paris.png";
import baliImg from "../assets/bali.png";
import yosemiteImg from "../assets/yosemite.png";
import catPaw from "../assets/cat-paw.png";

const BootstrapButton = styled(Button)({
    borderRadius: '9999px',
    fontWeight: '700',
    fontSize: '1rem',
    boxShadow: '0px 4px 12px rgba(0, 0, 0, 0.1)',
    textTransform: 'none',
    color: 'white',
    padding: '8px 20px',
});

export default function LandingPage() {
  const totalSteps = 10;
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % totalSteps);
    }, 2000); // One step every 2 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="landing-page-container">
      {/* Title */}
      <motion.h1
        className="app-title"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        Wanderlust - Your AI Trip Planner
      </motion.h1>

      {/* Cat Paw Stepper */}
      <div className="content-wrapper">
        <div className="cat-paw-strip">
            {[...Array(totalSteps)].map((_, i) => (
            <img
                key={i}
                src={catPaw}
                alt="cat paw"
                className={`cat-paw-print ${i === currentStep ? "active" : ""}`}
            />
            ))}
        </div>
      </div>

      {/* Feature Grid */}
      <div className="content-wrapper">
        <div className="features-grid">
            <div className="feature-card">🌍 Personalized trip plans based on your vibe.</div>
            <div className="feature-card">🧠 Messy Mind mode — know the dates, not the details.</div>
            <div className="feature-card">🏕️ Hotels, Airbnbs, camping — tailored for you.</div>
            <div className="feature-card">💰 Daily budgeting & smart suggestions.</div>
            <div className="feature-card">🔎 Search Instagram + YouTube for inspo.</div>
            <div className="feature-card">🧳 Save & refine your travel taste over time.</div>
        </div>
      </div>

      {/* Buttons Section */}
      <div className="content-wrapper">
        <div className="ai-options-grid">
            <Tooltip title="An interactive AI planner — perfect if you're figuring things out on the fly, with or without dates." arrow>
                <BootstrapButton
                    variant="contained"
                    style={{ backgroundColor: '#A855F7' }}
                    startIcon={<span className="emoji-icon">💬</span>}
                    component={Link}
                    to="/chat"
                >
                    Messy Mind Chat Planner
                </BootstrapButton>
            </Tooltip>

            <Tooltip title="Let AI build your dream trip based on your vibe and schedule." arrow>
                <BootstrapButton
                    variant="contained"
                    style={{ backgroundColor: '#2563EB' }}
                    startIcon={<span className="emoji-icon">📅</span>}
                    component={Link}
                    to="/personal-itinerary"
                >
                    Personalized Trip Planner
                </BootstrapButton>
            </Tooltip>

            <Tooltip title="Smart tips from real travelers, with influencer names & profiles you can trust." arrow>
                <BootstrapButton
                    variant="contained"
                    style={{ backgroundColor: '#15803D' }}
                    startIcon={<span className="emoji-icon">🔍</span>}
                >
                    Hidden Gems & Pro Tips
                </BootstrapButton>
            </Tooltip>
            </div>
      </div>

      {/* Image Sections */}
      <div className="content-wrapper">
        <div className="image-showcase">
            <div className="image-section">
            <img src={parisImg} alt="Paris" />
            <p>Romance in Paris 🇫🇷</p>
            </div>
            <div className="image-section">
            <img src={baliImg} alt="Bali" />
            <p>Spiritual escape in Bali 🌴</p>
            </div>
            <div className="image-section">
            <img src={yosemiteImg} alt="Yosemite" />
            <p>Nature calls in Yosemite 🏞️</p>
            </div>
        </div>
      </div>

      {/* Footer */}
      <div className="footer-note">
        Built by Ritika. I'm building this in my free time. ⌛ Work in progress. If you want to contribute, <a href="https://github.com/ritikamotwani/wanderlust" target="_blank" rel="noopener noreferrer">GitHub</a>
      </div>
    </div>
  );
}
