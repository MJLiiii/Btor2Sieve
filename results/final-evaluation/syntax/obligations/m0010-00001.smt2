(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(declare-fun s_11 () (Array (_ BitVec 8) (_ BitVec 32)))
(assert
 (let ((?x497 (ite (bvult (select s_11 i_6) ((_ zero_extend 24) (_ bv200 8))) (_ bv1 1) (_ bv0 1))))
 (let ((?x2625 (bvnot ?x497)))
 (let ((?x216 (bvand (_ bv1 1) ?x2625)))
 (not (= ?x216 (_ bv1 1)))))))
(assert
 (let ((?x5502 (select s_11 i_6)))
(let ((?x5498 ((_ extract 7 0) ?x5502)))
(let (($x133 (bvule (_ bv200 8) ?x5498)))
(let (($x2944 (or (not (= ((_ extract 31 8) ?x5502) (_ bv0 24))) $x133)))
(let (($x855 (not $x2944)))
(let (($x3628 (not $x855)))
(not $x3628))))))))
(check-sat)
