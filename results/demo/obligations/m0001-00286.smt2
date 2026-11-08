(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(declare-fun i_8 () (_ BitVec 4))
(declare-fun s_6 () (Array (_ BitVec 4) (_ BitVec 8)))
(assert
 (let ((?x9 (ite (and (distinct (select (store s_6 i_8 i_9) i_8) i_9) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x9 (_ bv1 1)))))
(assert
 (let ((?x27 (select s_6 i_8)))
(let (($x165 (bvule ?x27 (_ bv42 8))))
(not $x165))))
(check-sat)
