(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(declare-fun s_5 () (Array (_ BitVec 4) (_ BitVec 8)))
(assert
 (not (= (ite (and (distinct (_ bv0 8) (select s_5 s_6)) true) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x1276 (bvule s_6 (_ bv8 4))))
(not $x1276)))
(check-sat)
