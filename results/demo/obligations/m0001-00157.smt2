(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(declare-fun s_6 () (Array (_ BitVec 4) (_ BitVec 8)))
(assert
 (not (= (bvnot (ite (= (_ bv42 8) (select s_6 i_8)) (_ bv1 1) (_ bv0 1))) (_ bv1 1))))
(assert
 (let (($x137 (bvsle i_8 (_ bv1 4))))
(not $x137)))
(check-sat)
