(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(declare-fun s_11 () (Array (_ BitVec 8) (_ BitVec 32)))
(assert
 (let ((?x763 (ite (bvult (select s_11 i_6) ((_ zero_extend 24) (_ bv200 8))) (_ bv1 1) (_ bv0 1))))
 (let ((?x944 (bvnot ?x763)))
 (let ((?x47 (bvand (_ bv1 1) ?x944)))
 (not (= ?x47 (_ bv1 1)))))))
(assert
 (let (($x186 (= i_6 (_ bv200 8))))
(not $x186)))
(check-sat)
