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
 (let ((?x50 (store s_6 i_8 i_9)))
(let ((?x168 (select ?x50 i_8)))
(let (($x69 (= ?x168 (_ bv255 8))))
(not $x69)))))
(check-sat)
