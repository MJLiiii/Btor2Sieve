(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(declare-fun i_8 () (_ BitVec 4))
(declare-fun s_6 () (Array (_ BitVec 4) (_ BitVec 8)))
(declare-fun s_6_next () (Array (_ BitVec 4) (_ BitVec 8)))
(assert
 (let ((?x50 (store s_6 i_8 i_9)))
 (let (($x6 (= s_6_next ?x50)))
 (let (($x14 (and $x6)))
 (and $x14 true)))))
(assert
 (let (($x194 (and (distinct i_9 (_ bv255 8)) true)))
(not $x194)))
(check-sat)
