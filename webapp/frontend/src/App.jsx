import { Route, Routes } from "react-router-dom";

import { fetchGoldFormulaGraph, fetchMultimodalRetrievalAnnotated, fetchSilverFormulaGraph } from "./api";

import AnnotatedRetrievalView from "./components/AnnotatedRetrievalView";
import FormulaGraphPage from "./components/FormulaGraphPage";
import FormulaListView from "./components/FormulaListView";
import MultimodalRetrievalView from "./components/MultimodalRetrievalView";
import PostListView from "./components/PostListView";
import RetrievalView from "./components/RetrievalView";
import TopBar from "./components/TopBar";
import VocabView from "./components/VocabView";
import Task1EvaluationView from "./components/task1/Task1EvaluationView";
import Task1TopicView from "./components/task1/Task1TopicView";

export default function App() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route path="/" element={<PostListView />} />
        <Route path="/formulas" element={<FormulaListView />} />
        <Route path="/formula/:id" element={<FormulaGraphPage />} />
        <Route
          path="/gold_formula/:id"
          element={<FormulaGraphPage fetchGraph={fetchGoldFormulaGraph} titlePrefix="Gold formula" />}
        />
        <Route
          path="/silver_formula/:id"
          element={<FormulaGraphPage fetchGraph={fetchSilverFormulaGraph} titlePrefix="Silver formula" />}
        />
        <Route path="/vocab" element={<VocabView />} />
        <Route path="/retrieval" element={<RetrievalView />} />
        <Route path="/multimodal_retrieval" element={<MultimodalRetrievalView />} />
        <Route path="/annotated_retrieval" element={<AnnotatedRetrievalView />} />
        <Route
          path="/multimodal_retrieval_annotated"
          element={
            // key: don't carry the plain view's query/results over when switching tabs
            <MultimodalRetrievalView
              key="annotated"
              fetchPosts={fetchMultimodalRetrievalAnnotated}
              title="Annotated multimodal retrieval"
            />
          }
        />
        <Route path="/task1" element={<Task1EvaluationView />} />
        <Route path="/task1/topics/:topicId" element={<Task1TopicView />} />
      </Routes>
    </>
  );
}
